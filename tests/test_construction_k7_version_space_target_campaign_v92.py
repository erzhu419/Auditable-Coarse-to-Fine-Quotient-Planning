import pytest
from pathlib import Path

from acfqp import construction_k7_version_space_target_campaign_v92 as campaign
from acfqp.phase3e_ids import loads_canonical_json


def test_v92_frozen_campaign_refuses_reexecution_after_freeze():
    if campaign.CAMPAIGN_ID == "0" * 64:
        pytest.skip("V92 registered target campaign not executed yet")
    with pytest.raises(
        campaign.ConstructionK7VersionSpaceTargetCampaignV92Error,
        match="same identity will not be rerun",
    ):
        campaign.run_version_space_target_campaign_v92(b"", b"")


def test_v92_exact_failed_gate_is_preserved():
    document = loads_canonical_json(
        Path(
            ".tmp/exact-freeze/v92_version_space_target_campaign.json"
        ).read_bytes()
    )
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"][
        "completed_target_occurrence_count"
    ] == 1
    failed = document["target_occurrences"][0]
    assert failed["target_seed"] == 951101
    assert failed["failure_reason"] == (
        "V68 retained terminal tree missed the target prefix"
    )
    completed = document["target_occurrences"][1]["matched_ablation"]
    assert completed["derived_target_certificate_local_ground_support_labels"] == 11
    assert completed["strict_target_certificate_local_ground_support_labels"] == 11
