from pathlib import Path
import hashlib

from acfqp.construction_k7_occurrence_factor_bank_update_planning_preregistration_v142 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_occurrence_factor_bank_update_planning_preregistration_v142,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_occurrence_factor_bank_update_planning_preregistration_v142(
        (ROOT / "v141_occurrence_factor_bank_update.json").read_bytes(),
        (ROOT / "v141_occurrence_factor_bank_update_verification.json").read_bytes(),
        (ROOT / "v140_occurrence_factor_bank_planning_failure.json").read_bytes(),
    )


def test_v142_preregisters_occurrence_factor_bank_update_before_fresh_outcomes():
    registration = _freeze()
    document = registration.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["registered_v142_target_outcome_observed"] is False
    assert document["registered_gate"][
        "v141_occurrence_factor_bank_update_receipt_precedes_target_outcomes"
    ] is True
    assert document["registered_gate"][
        "occurrence_support_replaces_campaign_container_support"
    ] is True
    assert document["registered_gate"][
        "v140_preregistered_resource_cap_failure_preserved"
    ] is True
    assert document["maximum_acquisition_labels"] == 768
    assert len(document["target_occurrences"]) == 4
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v142_frozen_preregistration_bytes_when_registered():
    registration = _freeze()
    raw = registration.canonical_bytes
    if PREREGISTRATION_ID != "0" * 64:
        assert registration.preregistration_id == PREREGISTRATION_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
