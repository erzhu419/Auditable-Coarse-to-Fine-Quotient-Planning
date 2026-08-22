from pathlib import Path

from acfqp.construction_k7_relation_coverage_preregistration_v153 import freeze_relation_coverage_preregistration_v153


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v153_preregistration_is_outcome_free_and_operator_bound():
    document = freeze_relation_coverage_preregistration_v153((ROOT / "v153_relation_coverage_operator_receipt.json").read_bytes()).to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["frozen_operator_receipt"]["operator_extracted_before_v153_outcomes"] is True
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["official_scalar_cost"] is None
