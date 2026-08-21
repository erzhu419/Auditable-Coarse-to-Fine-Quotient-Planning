import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_identity_short_circuited_epoch_campaign_v111 as campaign


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v111_identity_short_circuited_epoch_campaign.json"
)


def test_v111_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(
        campaign.ConstructionK7IdentityShortCircuitedEpochCampaignV111Error
    ):
        campaign.run_identity_short_circuited_epoch_campaign_v111(b"", b"")


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN_PATH.exists(),
    reason="V111 fresh campaign has not been frozen",
)
def test_v111_exact_campaign_is_preserved():
    raw = CAMPAIGN_PATH.read_bytes()
    document = campaign.loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"]["passed_target_occurrence_count"] == 2
    assert document["registered_gate"][
        "aggregate_maintenance_strictly_below_full_diff"
    ] is True
    assert document["registered_identity_short_circuited_epoch_invalidation_verified"] is False
    failed = [
        row
        for row in document["target_occurrences"]
        if row["registered_gate"]["passed"] is False
    ]
    assert [(row["target_family"], row["seed"]) for row in failed] == [
        ("BALANCED_BATCH_REFINEMENT", 1_023_101),
        ("BALANCED_BATCH_REFINEMENT", 1_023_102),
    ]
    assert [
        row["accounting"]["maintenance_events_avoided_against_full_diff"]
        for row in failed
    ] == [-2, -2]
    assert document["cached_heuristic_used_as_safety_authority"] is False
    assert document["complete_ground_world_model_synthesized"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
