import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_post_dependency_campaign_v97 as campaign
from acfqp.phase3e_ids import loads_canonical_json


def test_v97_frozen_campaign_will_not_rerun_the_same_identity():
    assert campaign.pre.PREREGISTRATION_ID == (
        "99c6ae8e5c71ea1f5b92fc01117d979772d0958a255926beb81d032837b008fa"
    )
    assert campaign.CAMPAIGN_ID == (
        "b132245b0827898cb497232ed82b911fc17bebc4a30e981a7b080895abc8bf3e"
    )
    with pytest.raises(campaign.ConstructionK7PostDependencyCampaignV97Error):
        campaign.run_post_dependency_campaign_v97(b"", b"")


def test_v97_exact_successful_post_dependency_campaign_is_preserved():
    raw = Path(".tmp/exact-freeze/v97_post_dependency_campaign.json").read_bytes()
    document = loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert len(document["target_occurrences"]) == 4
    assert document["registered_gate"][
        "at_least_one_fresh_target_discovered_post_dependency_program"
    ] is True
    assert document["registered_gate"][
        "at_least_one_fresh_target_used_post_dependency_abstract_plan"
    ] is True
    assert document["accounting"]["meta_prior_lifetime_target_labels"] == 210
    assert document["accounting"]["no_structure_prior_lifetime_target_labels"] == 210
    assert document["accounting"]["strict_cold_direct_lifetime_target_labels"] == 387
    assert document["structural_prior_sample_tax_advantage_over_same_synthesizer_verified"] is False
    assert document["official_execution_allowed"] is False
