from pathlib import Path

from acfqp.construction_k7_plan_mode_margin_preregistration_v157 import freeze_plan_mode_margin_preregistration_v157


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v157_preregistration_is_fresh_outcome_free_and_two_worker_bounded():
    registration = freeze_plan_mode_margin_preregistration_v157(
        (ROOT / "v156_structural_margin_query_guard_receipt.json").read_bytes(),
        (ROOT / "v157_plan_mode_correction_receipt.json").read_bytes(),
    ).to_document()
    assert registration["target_worker_count"] == 2
    assert registration["required_target_occurrence_count"] == 8
    assert registration["claim_boundary"]["target_outcomes_accessed"] is False
    assert registration["claim_boundary"]["v156_failure_reclassified"] is False
    assert all(registration["registered_gate"].values())
