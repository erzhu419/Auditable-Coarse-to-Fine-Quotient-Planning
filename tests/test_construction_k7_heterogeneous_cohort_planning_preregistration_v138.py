from pathlib import Path
import hashlib

from acfqp.construction_k7_heterogeneous_cohort_planning_preregistration_v138 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_heterogeneous_cohort_planning_preregistration_v138,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_heterogeneous_cohort_planning_preregistration_v138(
        (ROOT / "v137_heterogeneous_archive_cohort_dictionary.json").read_bytes(),
        (ROOT / "v137_heterogeneous_archive_verification.json").read_bytes(),
    )


def test_v138_preregisters_heterogeneous_receipt_before_fresh_outcomes():
    registration = _freeze()
    document = registration.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["registered_v138_target_outcome_observed"] is False
    assert document["registered_gate"][
        "v137_heterogeneous_cohort_receipt_precedes_target_outcomes"
    ] is True
    assert document["registered_gate"][
        "incompatible_source_remains_explicitly_excluded"
    ] is True
    assert len(document["target_occurrences"]) == 4
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v138_frozen_preregistration_bytes_when_registered():
    registration = _freeze()
    raw = registration.canonical_bytes
    if PREREGISTRATION_ID != "0" * 64:
        assert registration.preregistration_id == PREREGISTRATION_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
