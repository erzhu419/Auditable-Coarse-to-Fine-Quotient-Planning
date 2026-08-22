from pathlib import Path

import pytest

from acfqp.construction_k7_structural_signature_guarded_preregistration_v155 import (
    PREREGISTRATION_ID,
    freeze_structural_signature_guarded_preregistration_v155,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v155_preregistration_precedes_guarded_target_outcomes():
    registration = freeze_structural_signature_guarded_preregistration_v155(
        (ROOT / "v155_structural_signature_query_guard_receipt.json").read_bytes()
    ).to_document()
    if PREREGISTRATION_ID == "0" * 64:
        pytest.skip("V155 preregistration not frozen")
    assert registration["preregistration_id"] == PREREGISTRATION_ID
    assert registration["target_worker_count"] == 2
    assert registration["claim_boundary"]["target_outcomes_accessed"] is False
    assert registration["claim_boundary"]["official_scalar_cost"] is None
