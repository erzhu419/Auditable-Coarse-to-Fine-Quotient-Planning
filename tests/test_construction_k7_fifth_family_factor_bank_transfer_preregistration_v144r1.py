from pathlib import Path
import hashlib

from acfqp.construction_k7_fifth_family_factor_bank_transfer_preregistration_v144r1 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_fifth_family_factor_bank_transfer_preregistration_v144r1,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_fifth_family_factor_bank_transfer_preregistration_v144r1(
        (ROOT / "v144_fifth_family_factor_bank_transfer_preregistration.json").read_bytes(),
        (ROOT / "v144_fifth_family_factor_bank_transfer_failure.json").read_bytes(),
    )


def test_v144r1_preserves_failure_and_preregisters_fresh_overlay_campaign():
    document = _freeze().to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["registered_v144r1_target_outcome_observed"] is False
    assert document["registered_gate"]["v144_identity_not_rerun"] is True
    assert document["registered_gate"][
        "query_local_exact_overlay_only_after_certificate_failure"
    ] is True
    assert document["registered_gate"]["source_partial_program_remains_immutable"] is True
    assert document["registered_gate"]["overlay_pipeline_must_be_exercised_at_least_once"] is True
    assert len(document["target_occurrences"]) == 6
    assert document["target_worker_count"] == 2
    assert document["maximum_acquisition_labels"] == 1_024
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v144r1_frozen_preregistration_bytes_when_registered():
    registration = _freeze()
    raw = registration.canonical_bytes
    if PREREGISTRATION_ID != "0" * 64:
        assert registration.preregistration_id == PREREGISTRATION_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
