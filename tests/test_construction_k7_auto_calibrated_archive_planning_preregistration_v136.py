from pathlib import Path
import hashlib

from acfqp.construction_k7_auto_calibrated_archive_planning_preregistration_v136 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_auto_calibrated_archive_planning_preregistration_v136,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_auto_calibrated_archive_planning_preregistration_v136(
        (ROOT / "v135_auto_calibrated_archive_dictionary.json").read_bytes(),
        (ROOT / "v135_auto_calibrated_archive_verification.json").read_bytes(),
    )


def test_v136_preregisters_auto_calibrated_receipt_before_fresh_outcomes():
    registration = _freeze()
    document = registration.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["registered_v136_target_outcome_observed"] is False
    assert document["registered_gate"][
        "v135_auto_calibrated_receipt_precedes_target_outcomes"
    ] is True
    assert document["registered_gate"]["support_thresholds_not_supplied_by_v136"] is True
    assert len(document["target_occurrences"]) == 4
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v136_frozen_preregistration_bytes_when_registered():
    registration = _freeze()
    raw = registration.canonical_bytes
    if PREREGISTRATION_ID != "0" * 64:
        assert registration.preregistration_id == PREREGISTRATION_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
