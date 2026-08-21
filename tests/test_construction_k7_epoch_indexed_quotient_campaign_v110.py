import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_epoch_indexed_quotient_campaign_v110 as campaign


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v110_epoch_indexed_quotient_campaign.json"
)


def test_v110_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(campaign.ConstructionK7EpochIndexedQuotientCampaignV110Error):
        campaign.run_epoch_indexed_quotient_campaign_v110(b"", b"")


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN_PATH.exists(),
    reason="V110 fresh campaign has not been frozen",
)
def test_v110_exact_campaign_is_preserved():
    raw = CAMPAIGN_PATH.read_bytes()
    document = campaign.loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"]["passed_target_occurrence_count"] == 3
    assert document["registered_gate"][
        "every_occurrence_dependency_maintenance_strictly_reduced"
    ] is False
    assert document["registered_epoch_indexed_dependency_invalidation_verified"] is False
    failed = [
        row
        for row in document["target_occurrences"]
        if row["registered_gate"]["passed"] is False
    ]
    assert [(row["target_family"], row["seed"]) for row in failed] == [
        ("MAINTENANCE_CASCADE", 1_022_103)
    ]
    assert failed[0]["accounting"]["epoch_indexed_dependency_maintenance_events"] == 346
    assert failed[0]["accounting"]["per_hit_dependency_validation_checks"] == 344
    assert document["cached_heuristic_used_as_safety_authority"] is False
    assert document["complete_ground_world_model_synthesized"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
