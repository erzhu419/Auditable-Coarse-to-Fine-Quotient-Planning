import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_dependency_revalidated_quotient_campaign_v109 as campaign


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v109_dependency_revalidated_quotient_campaign.json"
)


def test_v109_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(
        campaign.ConstructionK7DependencyRevalidatedQuotientCampaignV109Error
    ):
        campaign.run_dependency_revalidated_quotient_campaign_v109(b"", b"")


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN_PATH.exists(),
    reason="V109 fresh campaign has not been frozen",
)
def test_v109_exact_campaign_is_preserved():
    raw = CAMPAIGN_PATH.read_bytes()
    document = campaign.loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["registered_gate"]["passed_target_occurrence_count"] == 4
    assert document["registered_gate"][
        "every_occurrence_planning_compute_strictly_reduced"
    ] is True
    assert document[
        "registered_dependency_revalidated_quotient_reuse_verified"
    ] is True
    assert document["cached_heuristic_used_as_safety_authority"] is False
    assert document["complete_ground_world_model_synthesized"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
