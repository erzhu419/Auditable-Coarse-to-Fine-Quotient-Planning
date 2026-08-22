from pathlib import Path

from acfqp.relation_coverage_operator_receipt_v153 import freeze_relation_coverage_operator_receipt_v153


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v153_operator_receipt_precedes_new_outcomes_and_is_nonauthoritative():
    receipt = freeze_relation_coverage_operator_receipt_v153(
        (ROOT / "v151_relation_keyed_bank_campaign.json").read_bytes(),
        (ROOT / "v151_relation_keyed_bank_verification.json").read_bytes(),
        (ROOT / "v152_ternary_relational_transfer_campaign.json").read_bytes(),
        (ROOT / "v152_ternary_relational_transfer_verification.json").read_bytes(),
    ).to_document()
    assert receipt["operator_extracted_before_v153_outcomes"] is True
    assert receipt["operator"]["future_target_outcomes_accessed"] is False
    assert receipt["operator_is_query_order_heuristic_not_model_or_certificate_authority"] is True
    assert receipt["official_scalar_cost"] is None
