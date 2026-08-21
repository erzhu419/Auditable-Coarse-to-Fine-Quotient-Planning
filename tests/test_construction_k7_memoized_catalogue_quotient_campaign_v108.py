import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_memoized_catalogue_quotient_campaign_v108 as campaign


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v108_memoized_catalogue_quotient_campaign.json"
)


def test_v108_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(
        campaign.ConstructionK7MemoizedCatalogueQuotientCampaignV108Error
    ):
        campaign.run_memoized_catalogue_quotient_campaign_v108(b"", b"")


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN_PATH.exists(),
    reason="V108 fresh campaign has not been frozen",
)
def test_v108_exact_campaign_is_preserved():
    raw = CAMPAIGN_PATH.read_bytes()
    document = campaign.loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"]["passed_target_occurrence_count"] == 2
    assert document["registered_gate"][
        "every_occurrence_planning_compute_strictly_reduced"
    ] is False
    assert document[
        "registered_identity_bound_quotient_memoization_verified"
    ] is False
    assert document["accounting"]["planning_compute_events_avoided"] == 550
    assert document["complete_ground_world_model_synthesized"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
