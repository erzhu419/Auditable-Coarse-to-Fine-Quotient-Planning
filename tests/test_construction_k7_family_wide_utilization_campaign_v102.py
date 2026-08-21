import hashlib
from pathlib import Path
import pytest
from acfqp import construction_k7_family_wide_utilization_campaign_v102 as campaign
from acfqp.phase3e_ids import loads_canonical_json


def test_v102_frozen_campaign_will_not_rerun():
    assert campaign.pre.PREREGISTRATION_ID == "961025ca99438c31ecedaf33431f8ec95817f1b1d99fe9edda4886a8e1395ba2"
    assert campaign.CAMPAIGN_ID == "f0b45ab4a6466988ac6cef39bd2723869d7bb3d4409afc60b9d00e035609d3d7"
    with pytest.raises(campaign.ConstructionK7FamilyWideUtilizationCampaignV102Error): campaign.run_family_wide_utilization_campaign_v102(b"", b"", b"", b"")


def test_v102_exact_success_is_preserved():
    raw = Path(".tmp/exact-freeze/v102_family_wide_utilization_campaign.json").read_bytes(); doc = loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert doc["campaign_id"] == campaign.CAMPAIGN_ID
    assert doc["registered_gate"]["passed"] is True
    assert doc["registered_gate"]["passed_target_occurrence_count"] == 4
    assert doc["accounting"]["meta_abstract_execution_match_count"] == 45
    assert doc["accounting"]["meta_execution_step_count"] == 72
    assert doc["accounting"]["meta_activation"] == 173
    assert doc["accounting"]["no_prior_activation"] == 200
    assert all(row["both_shield_paths_observed_across_family"] for row in doc["family_wide_shield_path_coverage"])
    assert doc["complete_world_model_synthesized"] is False
