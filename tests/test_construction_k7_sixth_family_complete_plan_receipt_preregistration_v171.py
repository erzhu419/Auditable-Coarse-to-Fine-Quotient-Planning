from pathlib import Path
import hashlib

from acfqp.construction_k7_sixth_family_complete_plan_receipt_preregistration_v171 import (
    PREREGISTRATION_ID,
    TARGET_OCCURRENCES,
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    freeze_sixth_family_complete_plan_receipt_preregistration_v171,
)


ROOT = Path(__file__).resolve().parents[1]
FREEZE = ROOT / ".tmp/exact-freeze"


def test_v171_preregistration_is_outcome_free_and_requires_strict_sample_reduction():
    document = freeze_sixth_family_complete_plan_receipt_preregistration_v171().to_document()
    assert len(TARGET_OCCURRENCES) == 2
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"][
        "factor_prior_strict_acquisition_label_reduction_each_occurrence_required"
    ] is True
    assert document["registered_gate"][
        "complete_typed_plan_receipt_taxonomy_required"
    ] is True
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v171_frozen_preregistration_bytes():
    if PREREGISTRATION_ID == "0" * 64:
        return
    frozen = freeze_sixth_family_complete_plan_receipt_preregistration_v171()
    raw = (FREEZE / "v171_sixth_family_complete_plan_receipt_preregistration.json").read_bytes()
    assert frozen.canonical_bytes == raw
    assert frozen.preregistration_id == PREREGISTRATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
