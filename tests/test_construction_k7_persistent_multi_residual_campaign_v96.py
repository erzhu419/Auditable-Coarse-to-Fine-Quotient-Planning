import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_persistent_multi_residual_campaign_v96 as campaign
from acfqp.phase3e_ids import loads_canonical_json


def test_v96_frozen_failed_campaign_will_not_rerun_the_same_identity():
    assert campaign.pre.PREREGISTRATION_ID == (
        "535c2020329e2dc0d6d2c9742dd2be0ddd1b5ec447d9e891b8468d7cc16d0d85"
    )
    assert campaign.CAMPAIGN_ID == (
        "93d3ae84f1a1f2e1a6cb7dac3f72d5e5ef24646b2e9f864657fee3a242443551"
    )
    with pytest.raises(campaign.ConstructionK7PersistentMultiResidualCampaignV96Error):
        campaign.run_persistent_multi_residual_campaign_v96()


def test_v96_exact_unfavourable_result_is_preserved_without_selection():
    raw = Path(
        ".tmp/exact-freeze/v96_persistent_multi_residual_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is False
    assert document["accounting"]["meta_prior_lifetime_target_labels"] == 96
    assert document["accounting"]["no_residual_prior_lifetime_target_labels"] == 96
    assert document["accounting"]["strict_cold_direct_lifetime_target_labels"] == 174
    assert all(
        row["meta_prior_persistent_sequence"]["retained_joint_proposal_count"] == 0
        for row in document["target_occurrences"]
    )
    assert all(
        row["meta_prior_persistent_sequence"]["later_query_ground_support_labels"]
        == 0
        for row in document["target_occurrences"]
    )
    assert document["official_execution_allowed"] is False
