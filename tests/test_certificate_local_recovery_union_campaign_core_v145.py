from pathlib import Path

from acfqp.certificate_local_recovery_union_campaign_core_v145 import (
    reidentify_certificate_local_recovery_union_campaign_v145,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v145_corrects_overstrict_branch_gate_without_changing_observed_rows():
    source = loads_canonical_json(
        (ROOT / "v144r2_fifth_family_factor_bank_transfer_campaign.json").read_bytes()
    )
    result = reidentify_certificate_local_recovery_union_campaign_v145(
        source, preregistration_id="2" * 64
    )
    assert source["registered_gate"]["passed"] is False
    assert result["registered_gate"]["passed"] is True
    assert result["registered_gate"][
        "certificate_failure_local_recovery_exercised_at_least_once"
    ] is True
    assert result["registered_gate"]["observed_certificate_local_ground_label_count"] == 79
    assert result["registered_gate"]["observed_query_local_exact_overlay_edge_count"] == 0
    assert result["registered_gate"]["exact_overlay_branch_exercise_required"] is False
    assert result["accounting"] == source["accounting"]
    assert result["official_scalar_cost"] is None
