from pathlib import Path

import pytest

from acfqp.construction_k7_relation_coverage_cross_structure_preregistration_v154 import (
    PREREGISTRATION_ID,
    freeze_relation_coverage_cross_structure_preregistration_v154,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v154_preregistration_precedes_fresh_outcomes():
    registration = freeze_relation_coverage_cross_structure_preregistration_v154(
        (ROOT / "v154_relation_coverage_application_receipt.json").read_bytes()
    ).to_document()
    if PREREGISTRATION_ID == "0" * 64:
        pytest.skip("V154 preregistration not frozen")
    assert registration["preregistration_id"] == PREREGISTRATION_ID
    assert registration["target_worker_count"] == 2
    assert registration["claim_boundary"]["target_outcomes_accessed"] is False
    assert registration["claim_boundary"]["official_scalar_cost"] is None
