from pathlib import Path

from acfqp.fifth_family_factor_bank_transfer_campaign_core_v144r2 import (
    reidentify_fifth_family_factor_bank_transfer_campaign_v144r2,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v144r2_reidentifies_preserved_failed_campaign_without_changing_outcomes():
    source = loads_canonical_json(
        (ROOT / "v144r1_fifth_family_factor_bank_transfer_campaign.json").read_bytes()
    )
    result = reidentify_fifth_family_factor_bank_transfer_campaign_v144r2(
        source, preregistration_id="1" * 64
    )
    assert result["schema"].endswith("v144r2")
    assert result["preregistration_id"] == "1" * 64
    assert result["source_v144r1_campaign_semantics_id"] == source["campaign_id"]
    assert result["registered_gate"]["passed"] is False
    assert result["registered_gate"][
        "query_local_relational_overlay_exercised_at_least_once"
    ] is False
    assert result["accounting"] == source["accounting"]
    assert len(set(result["target_occurrence_ids"])) == len(
        result["target_occurrence_ids"]
    )
    assert all(
        row["v144r1_occurrence_semantics_reused_unchanged"] is True
        for row in result["target_occurrences"]
    )
