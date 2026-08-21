from pathlib import Path
import hashlib

from acfqp.construction_k7_third_family_owned_sequence_preregistration_v128 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_third_family_owned_sequence_preregistration_v128,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    return source, (ROOT / "v127_owned_sequence_cross_family_campaign.json").read_bytes(), (ROOT / "v127_owned_sequence_cross_family_verification.json").read_bytes()


def test_v128_preregistration_is_outcome_free_and_source_closed():
    registration = freeze_third_family_owned_sequence_preregistration_v128(*_inputs())
    document = registration.to_document()
    assert document["preregistration_id"] == PREREGISTRATION_ID
    assert document["source_closure"]["frozen_before_any_registered_v128_target_outcome"] is True
    assert document["identity_contract"]["target_family_absent_from_frozen_factor_artifact_sources"] is True
    assert document["claim_boundary"]["registered_v128_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
    if PREREGISTRATION_ID != "0" * 64:
        assert len(registration.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
        assert hashlib.sha256(registration.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
