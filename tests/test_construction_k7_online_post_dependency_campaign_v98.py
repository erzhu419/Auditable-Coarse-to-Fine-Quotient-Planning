import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_online_post_dependency_campaign_v98 as campaign
from acfqp.phase3e_ids import loads_canonical_json


def test_v98_frozen_campaign_will_not_rerun_the_same_identity():
    assert campaign.pre.PREREGISTRATION_ID == (
        "81b87ce48c3b4159e4e0e869228dbb34b02d06adf1b5ad7c2359ef2c8fa0e452"
    )
    assert campaign.CAMPAIGN_ID == (
        "0c81232368a76e987b9921e3312fa70653eb5cdbf18e077c8c482aa7bd827f6b"
    )
    with pytest.raises(campaign.ConstructionK7OnlinePostDependencyCampaignV98Error):
        campaign.run_online_post_dependency_campaign_v98(b"", b"", b"", b"")


def test_v98_exact_successful_activation_campaign_is_preserved():
    raw = Path(
        ".tmp/exact-freeze/v98_online_post_dependency_campaign.json"
    ).read_bytes()
    document = loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"]["post_dependency_occurrence_count"] == 3
    assert document["accounting"][
        "meta_model_activation_target_labels_with_right_censoring"
    ] == 178
    assert document["accounting"][
        "no_prior_model_activation_target_labels_with_right_censoring"
    ] == 206
    assert document["accounting"]["meta_lifetime_target_labels"] == 278
    assert document["accounting"]["no_prior_lifetime_target_labels"] == 278
    assert document["accounting"][
        "strict_cold_direct_lifetime_target_labels"
    ] == 441
    assert document[
        "structural_prior_model_activation_sample_tax_advantage_verified"
    ] is True
    assert document[
        "structural_prior_total_task_label_advantage_over_same_synthesizer_verified"
    ] is False
    assert document["complete_world_model_synthesized"] is False
    assert document["official_execution_allowed"] is False
