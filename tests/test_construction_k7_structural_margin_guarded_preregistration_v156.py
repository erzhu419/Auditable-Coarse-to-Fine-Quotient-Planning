from pathlib import Path

import pytest

from acfqp.construction_k7_structural_margin_guarded_preregistration_v156 import (
    PREREGISTRATION_ID,
    freeze_structural_margin_guarded_preregistration_v156,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def test_v156_preregistration_is_outcome_free_and_two_worker_bounded():
    registration = freeze_structural_margin_guarded_preregistration_v156(
        (ROOT / "v156_structural_margin_query_guard_receipt.json").read_bytes()
    ).to_document()
    if PREREGISTRATION_ID != "0" * 64:
        assert registration["preregistration_id"] == PREREGISTRATION_ID
    assert registration["target_worker_count"] == 2
    assert registration["required_target_occurrence_count"] == 8
    assert registration["claim_boundary"]["target_outcomes_accessed"] is False
    assert registration["claim_boundary"]["official_scalar_cost"] is None
    assert all(registration["registered_gate"].values())


def test_v156_preregistration_rejects_guard_mutation():
    raw = bytearray((ROOT / "v156_structural_margin_query_guard_receipt.json").read_bytes())
    raw[-2] ^= 1
    with pytest.raises(Exception):
        freeze_structural_margin_guarded_preregistration_v156(bytes(raw))
