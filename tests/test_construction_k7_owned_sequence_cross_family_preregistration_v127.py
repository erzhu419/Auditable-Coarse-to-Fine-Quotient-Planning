from pathlib import Path
import hashlib

from acfqp.construction_k7_owned_sequence_cross_family_preregistration_v127 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    PREREGISTRATION_ID,
    freeze_owned_sequence_cross_family_preregistration_v127,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    return source, (ROOT / "v126_standalone_generic_owned_campaign.json").read_bytes(), (ROOT / "v126_standalone_generic_owned_verification.json").read_bytes()


def test_v127_preregistration_is_outcome_free_cross_family_and_source_closed():
    registration = freeze_owned_sequence_cross_family_preregistration_v127(*_inputs())
    document = registration.to_document()
    assert document["preregistration_id"] == PREREGISTRATION_ID
    assert len(registration.canonical_bytes) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(registration.canonical_bytes).hexdigest() == EXPECTED_CANONICAL_SHA256
    assert document["construction_contract"]["unchanged_v126_owned_sequence_required"] is True
    assert document["construction_contract"]["family_dispatch_inside_owned_sequence_forbidden"] is True
    assert document["claim_boundary"]["registered_v127_target_outcome_observed"] is False
