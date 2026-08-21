from pathlib import Path
import hashlib

from acfqp.construction_k7_standalone_generic_owned_preregistration_v126 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_standalone_generic_owned_preregistration_v126,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    return (
        source,
        (ROOT / "v125_standalone_generic_model_campaign.json").read_bytes(),
        (ROOT / "v125_standalone_generic_model_verification.json").read_bytes(),
    )


def test_v126_preregistration_is_outcome_free_and_source_closed():
    registration = freeze_standalone_generic_owned_preregistration_v126(*_inputs())
    document = registration.to_document()
    assert document["preregistration_id"] == PREREGISTRATION_ID
    assert len(registration.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(registration.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["construction_contract"]["retained_v113_sequence_orchestration_present"] is False
    assert document["construction_contract"]["retained_v119_sequence_orchestration_present"] is False
    assert document["claim_boundary"]["registered_v126_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
