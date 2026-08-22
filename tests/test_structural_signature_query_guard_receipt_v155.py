from pathlib import Path

from acfqp.structural_signature_query_guard_receipt_v155 import (
    GUARD_RECEIPT_ID,
    freeze_structural_signature_query_guard_receipt_v155,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v155_guard_freezes_positive_and_failed_contexts_before_new_outcomes():
    receipt = freeze_structural_signature_query_guard_receipt_v155(
        (ROOT / "v153_relation_coverage_campaign.json").read_bytes(),
        (ROOT / "v153_relation_coverage_verification.json").read_bytes(),
        (ROOT / "v154_relation_coverage_cross_structure_campaign.json").read_bytes(),
        (ROOT / "v154_relation_coverage_cross_structure_failure.json").read_bytes(),
    ).to_document()
    assert receipt["guard_receipt_id"] == GUARD_RECEIPT_ID
    assert receipt["failed_source_operator_sample_reduction"] == -8
    assert receipt["selection_rule"]["unknown_signature_defaults_to_safe_fallback"] is True
    assert receipt["selection_rule"]["ground_successor_outcomes_accessed_by_guard"] is False
    assert receipt["official_scalar_cost"] is None
