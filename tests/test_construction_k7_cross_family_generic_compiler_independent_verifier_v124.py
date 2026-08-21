from pathlib import Path
import hashlib

from acfqp.construction_k7_cross_family_generic_compiler_independent_verifier_v124 import (
    EXPECTED_CANONICAL_BYTE_COUNT,
    EXPECTED_CANONICAL_SHA256,
    VERIFICATION_ID,
    freeze_cross_family_generic_compiler_verification_v124,
)
from acfqp.phase3e_ids import loads_canonical_json


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    names = (
        "v124_cross_family_generic_compiler_campaign.json",
        "v123r1_generic_quotient_compiler_campaign.json",
        "v123r1_generic_quotient_compiler_verification.json",
        "v122_generic_factor_planner_campaign.json",
        "v122_generic_factor_planner_verification.json",
        "v123_generic_quotient_compiler_failure.json",
        "v121r1_generic_subprogram_campaign.json",
        "v121_generic_artifact_subprogram_campaign.json",
        "v121r1_generic_subprogram_verification.json",
    )
    return (*tuple((ROOT / name).read_bytes() for name in names), source)


def test_v124_producer_free_cross_family_reconstruction():
    raw = freeze_cross_family_generic_compiler_verification_v124(*_inputs())
    document = loads_canonical_json(raw)
    assert document["registered_gate_independently_verified"] is True
    assert document["verified_family"] == "STOCHASTIC_INVENTORY_ASSEMBLY"
    assert sum(row["independently_rebuilt_model_epoch_count"] for row in document["verified_occurrences"]) == 12
    assert document["legacy_shape_specific_model_builder_called"] is False
    assert document["retained_v113_state_carrier_present"] is True
    assert document["official_scalar_cost"] is None


def test_v124_frozen_verification_bytes():
    raw = (ROOT / "v124_cross_family_generic_compiler_verification.json").read_bytes()
    document = loads_canonical_json(raw)
    assert document["verification_id"] == VERIFICATION_ID
    assert len(raw) == EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_CANONICAL_SHA256
