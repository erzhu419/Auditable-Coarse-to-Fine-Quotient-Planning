from pathlib import Path
import hashlib

from acfqp.construction_k7_certificate_local_recovery_union_preregistration_v145 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_certificate_local_recovery_union_preregistration_v145,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _freeze():
    return freeze_certificate_local_recovery_union_preregistration_v145(
        (ROOT / "v144r2_fifth_family_factor_bank_transfer_preregistration.json").read_bytes(),
        (ROOT / "v144r2_fifth_family_factor_bank_transfer_campaign.json").read_bytes(),
        (ROOT / "v144r2_fifth_family_factor_bank_transfer_failure.json").read_bytes(),
    )


def test_v145_preregisters_sound_recovery_union_before_fresh_outcomes():
    document = _freeze().to_document()
    assert document["claim_boundary"]["target_outcomes_accessed"] is False
    assert document["registered_gate"]["v144r2_identity_not_rerun"] is True
    assert document["registered_gate"][
        "certificate_failure_local_recovery_must_be_exercised"
    ] is True
    assert document["registered_gate"]["exact_overlay_branch_exercise_required"] is False
    assert document["gate_correction_rationale"][
        "program_compatible_incremental_refinement_is_sound_local_recovery"
    ] is True
    assert len(document["target_occurrences"]) == 6
    assert len(document["target_episode_indices"]) == 4
    assert document["target_worker_count"] == 2
    assert document["claim_boundary"]["official_scalar_cost"] is None


def test_v145_frozen_preregistration_bytes_when_registered():
    registration = _freeze()
    if PREREGISTRATION_ID != "0" * 64:
        assert registration.preregistration_id == PREREGISTRATION_ID
        assert len(registration.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(registration.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
