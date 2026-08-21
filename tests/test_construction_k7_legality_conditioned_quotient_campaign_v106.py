import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_legality_conditioned_quotient_campaign_v106 as campaign


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v106_legality_conditioned_quotient_campaign.json"
)


def test_v106_producer_rejects_missing_predecessors_before_outcomes():
    with pytest.raises(
        campaign.ConstructionK7LegalityConditionedQuotientCampaignV106Error
    ):
        campaign.run_legality_conditioned_quotient_campaign_v106(b"", b"")


@pytest.mark.skipif(
    campaign.CAMPAIGN_ID == "0" * 64 or not CAMPAIGN_PATH.exists(),
    reason="V106 fresh campaign has not been frozen",
)
def test_v106_exact_campaign_is_preserved():
    raw = CAMPAIGN_PATH.read_bytes()
    document = campaign.loads_canonical_json(raw)
    assert len(raw) == campaign.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == campaign.EXPECTED_CANONICAL_SHA256
    assert document["campaign_id"] == campaign.CAMPAIGN_ID
    assert document["registered_gate"]["passed"] is False
    assert document["registered_gate"]["passed_target_occurrence_count"] == 2
    assert document["registered_gate"][
        "every_occurrence_actual_quotient_ordering_at_least_three_quarters"
    ] is True
    assert document["accounting"]["execution_steps"] == 65
    assert document["accounting"][
        "quotient_proposal_admitted_execution_count"
    ] == 65
    assert document["accounting"][
        "chosen_action_matches_admitted_quotient_proposal_count"
    ] == 53
    assert document["accounting"]["quotient_lifetime_target_labels"] == 258
    assert document["accounting"]["cold_direct_lifetime_target_labels"] == 588
    assert document[
        "registered_execution_primarily_ordered_by_legality_conditioned_quotient"
    ] is False
    assert document["complete_ground_world_model_synthesized"] is False
    assert document["official_scalar_cost"] is None
    assert document["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"
