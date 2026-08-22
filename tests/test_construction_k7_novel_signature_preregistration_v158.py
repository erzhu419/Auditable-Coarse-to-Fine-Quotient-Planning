from pathlib import Path

from acfqp.construction_k7_novel_signature_preregistration_v158 import freeze_novel_signature_preregistration_v158


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v158_preregistration_is_outcome_free_and_resource_bounded():
    registration = freeze_novel_signature_preregistration_v158((ROOT / "v158_anonymous_query_classifier_receipt.json").read_bytes()).to_document()
    assert registration["target_worker_count"] == 2
    assert registration["required_target_occurrence_count"] == 8
    assert registration["claim_boundary"]["target_outcomes_accessed"] is False
    assert registration["claim_boundary"]["official_scalar_cost"] is None
    assert all(registration["registered_gate"].values())
