from pathlib import Path

import pytest

from acfqp import construction_k7_incremental_abstract_successor_campaign_v113 as campaign


ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / ".tmp/exact-freeze/v113_incremental_abstract_successor_campaign.json"


def test_v113_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(
        campaign.ConstructionK7IncrementalAbstractSuccessorCampaignV113Error
    ):
        campaign.run_incremental_abstract_successor_campaign_v113(b"", b"")


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN.exists(),
    reason="V113 fresh campaign has not been frozen",
)
def test_v113_exact_campaign_is_preserved():
    raw = CAMPAIGN.read_bytes()
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    document = campaign.loads_canonical_json(raw)
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is True
    assert document["registered_incremental_abstract_successor_verified"] is True
    assert document["accounting"][
        "incremental_model_update_compilation_events"
    ] < document["accounting"][
        "matched_full_rebuild_update_compilation_events"
    ]
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
