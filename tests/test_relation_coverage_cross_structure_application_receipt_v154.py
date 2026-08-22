from pathlib import Path

from acfqp.relation_coverage_cross_structure_application_receipt_v154 import (
    APPLICATION_RECEIPT_ID,
    freeze_relation_coverage_cross_structure_application_receipt_v154,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v154_application_receipt_is_outcome_free_and_nonauthoritative():
    receipt = freeze_relation_coverage_cross_structure_application_receipt_v154(
        (ROOT / "v153_relation_coverage_operator_receipt.json").read_bytes(),
        (ROOT / "v153_relation_coverage_campaign.json").read_bytes(),
        (ROOT / "v153_relation_coverage_verification.json").read_bytes(),
    ).to_document()
    assert receipt["application_receipt_id"] == APPLICATION_RECEIPT_ID
    assert receipt["registered_application"]["fresh_target_outcomes_accessed"] is False
    assert receipt["registered_application"]["nonrelational_anonymous_schema_ood_must_reject_before_bank_access"] is True
    assert receipt["operator_remains_query_order_heuristic_not_model_or_certificate_authority"] is True
    assert receipt["official_scalar_cost"] is None
