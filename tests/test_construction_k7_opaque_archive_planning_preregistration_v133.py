from pathlib import Path
import hashlib

from acfqp.construction_k7_opaque_archive_planning_preregistration_v133 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_opaque_archive_planning_preregistration_v133,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_opaque_archive_planning_preregistration_v133(
        (ROOT / "v132_opaque_source_archive_dictionary.json").read_bytes(),
        (ROOT / "v132_opaque_source_archive_verification.json").read_bytes(),
    )


def test_v133_preregisters_receipt_before_fresh_outcomes():
    registration = _freeze()
    document = registration.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["registered_v133_target_outcome_observed"] is False
    assert document["registered_gate"][
        "v132_dictionary_receipt_precedes_target_outcomes"
    ] is True
    assert len(document["target_occurrences"]) == 6
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v133_frozen_preregistration_bytes_when_registered():
    registration = _freeze()
    raw = registration.canonical_bytes
    if PREREGISTRATION_ID != "0" * 64:
        assert registration.preregistration_id == PREREGISTRATION_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
