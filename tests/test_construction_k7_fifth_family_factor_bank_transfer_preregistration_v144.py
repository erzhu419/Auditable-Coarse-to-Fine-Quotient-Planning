from pathlib import Path
import hashlib

from acfqp.construction_k7_fifth_family_factor_bank_transfer_preregistration_v144 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_fifth_family_factor_bank_transfer_preregistration_v144,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_fifth_family_factor_bank_transfer_preregistration_v144(
        (ROOT / "v141_occurrence_factor_bank_update.json").read_bytes(),
        (ROOT / "v141_occurrence_factor_bank_update_verification.json").read_bytes(),
    )


def test_v144_preregisters_source_unseen_fifth_family_before_fresh_outcomes():
    registration = _freeze()
    document = registration.to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["claim_boundary"]["registered_v144_target_outcome_observed"] is False
    assert document["claim_boundary"]["source_unseen_relative_to_v141"] is True
    assert document["claim_boundary"]["globally_unseen_kernel_claimed"] is False
    assert document["registered_gate"][
        "finite_relations_lowered_before_planning"
    ] is True
    assert document["registered_gate"][
        "historical_v121_v122_modules_unchanged"
    ] is True
    assert document["registered_gate"][
        "aggregate_positive_reduction_is_primary_gate"
    ] is True
    assert document["registered_gate"][
        "strict_positive_reduction_required_each_occurrence"
    ] is False
    assert len(document["target_occurrences"]) == 6
    assert document["target_worker_count"] == 2
    assert document["maximum_acquisition_labels"] == 1_024
    assert document["claim_boundary"]["official_scalar_cost"] is None
    assert document["claim_boundary"]["WORKLOAD_ECONOMICS_GATE"] == "NOT_RUN"


def test_v144_frozen_preregistration_bytes_when_registered():
    registration = _freeze()
    raw = registration.canonical_bytes
    if PREREGISTRATION_ID != "0" * 64:
        assert registration.preregistration_id == PREREGISTRATION_ID
        assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
