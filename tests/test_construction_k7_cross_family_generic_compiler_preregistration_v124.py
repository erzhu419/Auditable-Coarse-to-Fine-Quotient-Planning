from pathlib import Path

from acfqp.construction_k7_cross_family_generic_compiler_preregistration_v124 import (
    MAXIMUM_ACQUISITION_LABELS,
    TARGET_EPISODE_INDICES,
    TARGET_OCCURRENCES,
    freeze_cross_family_generic_compiler_preregistration_v124,
)


ROOT = Path(__file__).resolve().parents[1] / ".tmp/exact-freeze"


def _inputs():
    source = {
        "V117": (ROOT / "v117_dependency_derived_program_branch_campaign.json").read_bytes(),
        "V118": (ROOT / "v118_fourth_family_inventory_campaign.json").read_bytes(),
        "V119": (ROOT / "v119_source_unseen_residual_campaign.json").read_bytes(),
    }
    return source, (ROOT / "v123r1_generic_quotient_compiler_campaign.json").read_bytes(), (ROOT / "v123r1_generic_quotient_compiler_verification.json").read_bytes()


def test_v124_preregistration_is_fresh_cross_family_and_outcome_free():
    value = freeze_cross_family_generic_compiler_preregistration_v124(*_inputs())
    document = value.to_document()
    assert tuple((row["family"], row["seed"]) for row in document["identity_contract"]["target_occurrences"]) == TARGET_OCCURRENCES
    assert tuple(document["identity_contract"]["target_episode_indices"]) == TARGET_EPISODE_INDICES
    assert document["resource_schedule"]["maximum_acquisition_labels"] == MAXIMUM_ACQUISITION_LABELS
    assert document["construction_contract"]["legacy_shape_specific_model_builder_called"] is False
    assert document["claim_boundary"]["registered_v124_target_outcome_observed"] is False
    assert document["claim_boundary"]["official_scalar_cost"] is None
