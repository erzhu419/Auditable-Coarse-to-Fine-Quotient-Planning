from pathlib import Path

from acfqp.construction_k7_ternary_relational_transfer_preregistration_v152 import freeze_ternary_relational_transfer_preregistration_v152


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v152_preregistration_is_outcome_free():
    result = freeze_ternary_relational_transfer_preregistration_v152(
        (ROOT / "v151_relation_keyed_bank_campaign.json").read_bytes(),
        (ROOT / "v151_relation_keyed_bank_verification.json").read_bytes(),
    )
    document = result.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"]["two_key_source_to_three_key_target_required"] is True
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["official_scalar_cost"] is None
