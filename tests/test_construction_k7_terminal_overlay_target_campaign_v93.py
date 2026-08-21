import hashlib
from pathlib import Path

import pytest

from acfqp.phase3e_ids import loads_canonical_json

from acfqp import construction_k7_terminal_overlay_target_campaign_v93 as campaign


def test_v93_frozen_failure_will_not_be_rerun_under_the_same_identity():
    assert campaign.CAMPAIGN_ID == (
        "1b9b2fb6a1a837428c40d7d4b42546d1bed75fb406f53a5d84af0c69d25b891e"
    )
    with pytest.raises(campaign.ConstructionK7TerminalOverlayTargetCampaignV93Error):
        campaign.run_terminal_overlay_target_campaign_v93(b"", b"", b"", b"")


def test_v93_exact_failed_campaign_is_preserved():
    raw = Path(
        ".tmp/exact-freeze/v93_terminal_overlay_target_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"][
        "completed_target_occurrence_count"
    ] == 2
    assert document["registered_gate"][
        "every_target_certificate_label_reduction_observed"
    ] is False
    assert document["accounting"]["derived_target_certificate_local_labels"] == 13
    assert document["accounting"]["strict_target_certificate_local_labels"] == 14
    assert document["accounting"]["target_joint_acquisition_labels"] == 38
    assert document["multi_step_planning_primarily_in_abstract_model_verified"] is False
    assert document["official_execution_allowed"] is False
